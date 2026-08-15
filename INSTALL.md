# START HERE — setting up your Lifehack Brain

You are about to give yourself an AI that remembers you.

**This file sets up one thing: `/ingest`.** It takes a pile of your own material — an old ChatGPT
export, a folder of notes, a stack of documents — and turns it into a folder structure that you and your
AI can both work from. That is the only skill this file walks you through, and the only one you need to
know about today.

⚠ **It is not the only thing that arrives.** The same download brings a working set of other skills too
— for keeping a project's memory straight, thinking a decision through, and (once you connect your own
Google account) working your calendar, tasks and spreadsheets. None of that needs setup beyond what this
file already does, and teaching it is not this file's job — see `README.md` for what else is here, and
this file's own "THE GOOGLE-CONNECTED PARTS" section below if you're wondering what a Google connection
would actually let it do. You meet the rest later, the way you're meeting `/ingest` today.

**This file is the whole setup.** You don't need to know anything technical. You don't need a terminal.
You hand this file to Claude and answer its questions.

---

## What it builds — one folder, and everything lives inside it

    AI Brain/                 <- the ONE folder you open. every time. THIS folder IS the tool.
    ├── .claude/                 the commands — this is where Claude looks
    ├── system/                  the programs that do the sorting
    ├── shared/                  the piece that knows where your writing lives
    └── data/                    everything you write. yours. never uploaded, never tracked.
        └── desks/               a folder per subject, once you've run an ingest

**You open that folder. That's the only thing to remember.**

Setup builds all of it for you. **You are asked exactly one question: where to put the top folder.**

⭐ **The tool unpacks directly into the folder you open — there is no inner `lifehack-brain` folder.**
That is deliberate, and it is what makes the `/ingest` command appear at all. Claude only looks for
commands in the folder you actually opened; when they sat one level down, it could not see them.

⚠ **Your writing lives in `data`, INSIDE that folder, and git is told to ignore it.** It is never
tracked, never committed, never uploaded. **The one rule that follows from this: take updates with
`git pull` — never by deleting this folder and downloading a fresh copy.** A pull leaves `data`
completely alone. Deleting the folder takes your writing with it. See the end of this file.

**Back up `data` however you already back things up.** It's the part that's yours and can't be
re-downloaded — everything else here is one `git clone` away.

## What you do — about ten minutes

**1. Make a folder and open it in Claude.** Call it whatever you like — "AI Brain" is the usual. Put it
somewhere ordinary like your Documents folder. Then: Claude desktop app, the **Code** tab, open that
folder.

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

**Wondering what this needs from outside itself, or whether any of it costs money?**
`docs/OUTSIDE-SERVICES.md` covers every one of them in one place — and only two, out of eleven, are
actually required to install this at all.

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
> ## ⛔⛔ NEVER PUT THEIR MATERIAL INSIDE THE AI BRAIN FOLDER. NOT THE ZIP, NOT THE UNZIPPED COPY.
>
> **Their export stays where it already is** — Downloads, Desktop, wherever. ⛔ **Do not copy it in, do not
> move it in, and do not unzip it into this folder or any folder underneath it — `data` included.**
>
> ⚠ **THIS RULE GOT SHARPER, NOT SOFTER, WHEN THE LAYOUT CHANGED.** The tool now unpacks straight into
> the folder they opened, so **the AI Brain folder IS the git repository.** There is no longer a
> "safe outer folder" to drop things into. Everything except `data` is tracked by git the moment it
> appears.
>
> ⭐ **WHY — watched happening 2026-08-09, under the old layout.** A session was asked to "extract the zip
> to a folder" and extracted it inside the tool folder. That folder is version-controlled, so **git
> instantly began tracking 6,228 changes** — including the export's own `users.json`, which carries the
> person's **email address and phone number.** It could not actually reach the public repository (they
> hold no upload credentials), but the folder was polluted and their private history was staged for
> upload.
>
> **The rule, restated for this layout:** *nothing of the person's may ever be tracked by git.* `data` is
> the single exception, and only because `.gitignore` explicitly excludes it. **Their raw material has no
> exception — it stays outside the AI Brain folder entirely.**
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

> ⚠ **Why this resolves the interpreter instead of just typing `python3`.** On Windows, the word
> `python3` does not reliably exist yet at this point in the install — STEP 3's own TRAP 2 fix removes
> the Microsoft Store's decoy `python3.exe`, and the real one that STEP 7 creates in its place
> (`system/tools/bootstrap.py`'s shim) has not run yet. `python`, or `python3`, whichever answered in
> STEP 3, is what is actually there. This same pattern is used again at the start of STEP 7, for the
> same reason.

```bash
PYBIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
"$PYBIN" - "$PWD" <<'PY'
import os, re, sys
p = os.path.realpath(sys.argv[1]); low = p.replace("\\", "/").lower() + "/"
prot  = ["/program files", "/programdata", "/windows/", "/system/"]
if re.fullmatch(r"[a-z]:/users/?", low) or low in ("/users/", "/home/"):
    print("PROTECTED - the bare users folder"); sys.exit(3)
hit = next((t for t in prot if t in low), None)
if hit: print("PROTECTED SYSTEM FOLDER - matched: %s" % hit.strip("/")); sys.exit(3)
comps = [c for c in low.split("/") if c]
cloud = ["dropbox", "google drive", "onedrive", "icloud", "mobile documents"]
chit = next((t for t in cloud if t in comps), None)
if not chit and any(c == "googledrive" or c.startswith("googledrive-") for c in comps):
    chit = "googledrive"
if chit: print("CLOUD-SYNC FOLDER - matched: %s" % chit); sys.exit(4)
print("GOOD"); sys.exit(0)
PY
```

**`GOOD` → say nothing about it and carry straight on to STEP 5.**

**`CLOUD-SYNC FOLDER` → this is a safety gate, not a preference, and the reason is different from the
system-folder case below — say so.** A folder synced by Google Drive, Dropbox, OneDrive or iCloud Drive
rewrites files out from under git while the tool is mid-clone or mid-write, and that can corrupt the
repository — measured, not a guess. Say plainly: *"This folder syncs through <service>, and that can
corrupt the tool while it's installing — let's use a folder that doesn't sync, like your Documents
folder or a plain folder in your home directory."* Then: *"Quit Claude, open it again on that folder,
and drag this file in again."* **Then STOP**, same as the next case.

**Anything else (`PROTECTED...`) → this is the other time you ask them something.** Say plainly why this
spot won't work — *"this is a system folder and the tool can't be installed into it"* — then: *"Quit
Claude, open it again on an ordinary folder — your Documents folder is a good spot — and drag this file
in again."* **Then STOP.** Do not try to create a folder elsewhere and carry on; they must reopen the
session there, or nothing the tool does later will be able to reach it.

> ⛔ **Never test writability by asking for administrator rights.** If a write fails anywhere in this
> install, the answer is a different folder, never elevation. **A real student lost their install to
> exactly that detour on 2026-08-12.**

## STEP 5 — Fetch the tool INTO the folder you're already in — note the trailing dot

```bash
git clone -b migration-1 https://github.com/LifehackMethod/lifehack-brain.git .
```

**`-b migration-1` is the version currently being tested** — it is ahead of the default one. Without it
you get an older release with known bugs.

**The `.` on the end is the whole point.** It unpacks the tool *into* the folder they already opened,
rather than making a `lifehack-brain` subfolder inside it. ⛔ Do not `cd` anywhere first, and do not
drop the dot.

> ⛔⛔ **WHY THE DOT — CHANGED 2026-08-12, AND THE OLD WAY SILENTLY DID NOT WORK.**
> The tool used to clone into a `lifehack-brain` subfolder, and the instructions said the commands
> would be found from the folder above it. **They were not.** Claude only loads commands from the
> folder you actually open. A `.claude` folder one level down is not read at startup, so `/ingest`
> simply never appeared — **with no error, and nothing to search for.** Putting the repository at the
> top level is what fixes it.
>
> ⚠ **A second, separate trap sat underneath that one, and it is worth knowing about because it looks
> identical.** If the tool ever ends up in a folder *below* the one you opened, Claude also treats it as
> a different, untrusted project — and refuses to load its commands until that folder is trusted in its
> own right. **Same symptom, different cause. Both are cured by cloning to the top level.**

Confirm it landed:
```bash
ls .claude/skills/ingest/SKILL.md && echo "the skill is here"
```

**Tell them what arrived**, in a sentence: the tool itself, and the specialist readers it uses.

⛔ **Do NOT symlink anything into `~/.claude/`.** Symlinks are Mac-coupled and this has to work on
Windows too.

> ⛔ **If `git clone` refuses because the folder is not empty**, do NOT `git init` it and do NOT merge by
> hand. Find out what is in there first:
>
> ```bash
> ls -A
> ```
>
> **If it is an older copy of the tool**, ask whether they can rename or delete it, then clone again.
> **If it is a `data` folder from a previous install, that is their writing — do not delete it.** Move
> it aside, clone, then move it back:
>
> ```bash
> mv data ../data-keep && git clone https://github.com/LifehackMethod/lifehack-brain.git . && mv ../data-keep data
> ```

## STEP 6 — Confirm the pieces arrived, and turn on the safety catch

```bash
test -f .claude/skills/ingest/SKILL.md && test -d .claude/agents && echo "FILES OK" || echo "FILES MISSING"
```

**If `FILES OK`**, turn on the catch that keeps their own writing out of the repository:

```bash
git config core.hooksPath system/githooks && echo "SAFETY CATCH ON"
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
> ⭐ **There is no decision here. `data` sits inside the AI Brain folder. That is the design.**

```bash
mkdir -p data
PYBIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
"$PYBIN" shared/brain_root.py --set "$PWD/data"
"$PYBIN" system/tools/bootstrap.py
```

⚠ **Same `PYBIN` resolution as STEP 4, and it matters most right here:** the second of these two
commands is what CREATES the `python3` shim on Windows, so it cannot itself assume `python3` already
works. Everything from here on — STEP 8 onward, and every skill afterwards — can go back to plain
`python3`, because this step is what makes that word actually resolve.

⛔ **Read what `--set` printed before moving on. If it says `⚠ REPLACED a brain root that was already
set`, STOP and tell them.** That line means this machine already had a brain somewhere else — an
earlier install, a second folder, another person's account — and it now points here instead. The
value lives in `~/.config/lifehack/brain-root`, which is OUTSIDE the repo, so deleting a tool folder
and re-cloning never resets it (issue #4, 2026-08-12).

> **Say it plainly and let them choose:** *"Heads up — this machine already had an AI Brain pointed at
> `<the old path>`. I've just pointed everything at the new one. If that old folder is still the one
> you use, say so and I'll put it back."* The command to restore it is printed right there in the
> warning. **No warning printed → say nothing; this is a first install and there is nothing to tell.**

⚠ **This step is what settles the brain root, so `/ingest` will find it already answered.** The ingest
skill's step 1.0 owns the question *only when nothing is recorded yet* — on a normal install it reads
the value set here, says the path out loud, and does not ask (issue #6, 2026-08-12). **That is correct
and not a bug to fix by making it ask again.**

**Now prove git is ignoring it.** `data` lives *inside* the repository, so this is the line that keeps
their writing out of version control — and a check you skip is a check that failed.

```bash
git check-ignore -q data && echo "DATA IS IGNORED — good" || echo "⛔ DATA IS NOT IGNORED — STOP"
```

⛔ **If it says `NOT IGNORED`, stop and fix it before going further.** The `.gitignore` that ships with
the tool already lists `data/`; if the check fails, the clone is incomplete or something overwrote it.
Re-run **STEP 5**. **Do not carry on and do not `git add` anything** — an ingest run into an untracked-
but-not-ignored `data` is exactly how someone's private history gets staged for upload.

**Then say what you made, in one plain sentence, and move on:** *"Your writing goes in a folder called
`data`, inside your AI Brain. I've put a journal, a project list and somewhere for project notes in
there — they fill themselves in as you work. Git is set to ignore it completely, so none of it can ever
be uploaded."*

⛔ **`desks/` is NOT created here.** Those appear inside `data` the first time they run an ingest, one
per subject, built from their own material. **Do not pre-create them and do not invent subject names.**

---

### ⚠ Then mention backups — ONCE, as a recommendation. It is NOT a requirement and NOT a gate.

**Say this, and accept whatever they say back:**

> *"One thing worth doing when you have a minute: make sure the `data` folder is somewhere that gets
> backed up — however you already back things up. It's the part that's yours and can't be
> re-downloaded. Everything else here I can fetch again in a second. Not required, and it can wait."*

If they want a copy right now, give them the one line and let them run it:

```bash
cp -R "$PWD/data" ~/brain-backup-$(date +%F)
```

⛔ **Do NOT set up a backup or sync client for them, do NOT walk them through the menus now, and do NOT
block the install on it.** They are ten minutes into a setup and this is the least urgent thing in the
file.

## STEP 8 — Prove it can actually run, before you promise them anything

**A check you skipped is not a check that passed.**

```bash
python3 -c "import sys; sys.path.insert(0,'system/tools/cowork-ingest'); import pipeline; print('TOOLS OK')"
```

**If it does not print `TOOLS OK`, stop.** Tell them plainly the install is incomplete and read them the
last line of the error. **Do not tell them to try `/ingest` anyway.**

Then confirm the shape — **the tool at the top level, `data` beneath it:**
```bash
test -d .claude && test -d system && test -d shared && test -d data && echo "SHAPE OK" || echo "SHAPE WRONG"
```
⛔ **If it says `SHAPE WRONG`, something went wrong** — say so rather than continuing. The most likely
cause is a clone without the trailing dot in **STEP 5**, which buries everything in a `lifehack-brain`
subfolder. Check with `ls -A`; if you see one, that is the fault.

**Last, prove nothing of theirs is staged for upload.** This is the check that matters most:
```bash
git status --porcelain
```
⛔ **It must print NOTHING AT ALL.** Empty output means `data` is properly ignored and no stray file has
crept into the repository. **If anything is listed, stop and read it out** — do not commit it, do not
`git add` it, and do not continue until you understand what it is.

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

⭐ **Give them the literal path. They reopen the SAME folder they're in now** — the AI Brain folder
itself, the one holding `.claude` and `data`. **Not `data`, and not any folder inside it.** This is the
folder the commands live in; open anything below it and `/ingest` will not exist.

⚠ **If they installed before the 2026-08-12 layout change, they will go hunting for an inner
`lifehack-brain` folder, because the old instructions told them to open the folder above it. There
isn't one any more — the tool IS this folder. Say so explicitly**, or they will open the parent
directory out of habit and land somewhere with no tool in it at all.

Then **STOP. Do not continue this file. Do not offer to run `/ingest` yourself.**

## STEP 10 — After they restart (the first thing to do in the NEW session)

Confirm the command exists before they type anything:

```bash
ls .claude/skills/ingest/SKILL.md
```

⭐ **You are in the AI Brain folder and the tool is right here in it, not one level down. That is
correct and is how it should look.**

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
There is a complete manual backup: **`.claude/skills/ingest/PLAN-B.md`**, inside the ingest skill's own
folder — it belongs to that skill, not to the tool as a whole.
Drag it into a **fresh** Claude conversation and say **"help me."** It walks your AI through the same
process by hand, without needing any of the tools to work. You get the same result; it just takes longer.

**4. Your own material — an export, notes, anything of yours — ended up tracked by git.**
This is the mistake the block above (**"NEVER PUT THEIR MATERIAL INSIDE THE AI BRAIN FOLDER"**) exists to
prevent, but if it already happened — an old install, a copy-paste, anything — there is a safe recovery:
run `sh system/tools/untrack-my-stuff.sh` from the top of this folder. It only ever runs `git rm --cached`,
so it stops git from tracking your files and **never deletes anything from disk.**

---

# WHAT'S IN HERE, AND WHY IT'S SPLIT THIS WAY

```
AI Brain/                        <- YOU OPEN THIS ONE. always. every session. IT IS the tool.
│
│   ── THE FOUR PAGES WRITTEN FOR YOU. Read in this order if you ever need them. ──
├── INSTALL.md                       this file. setup, start to finish.
├── README.md                        what this thing is, in a page.
├── UPDATE.md                        getting a fix once it exists → the short answer is `git pull`
│
│   ── THE MACHINERY. You never need to open any of it. ──
├── .claude/                         the commands — this is where Claude looks
│   ├── agents/                      the specialist readers the tool uses
│   ├── skills/                      the tools themselves — `/ingest` plus a working set of others;
│   │   │                            README.md names what's here, or just type `/` to browse them
│   │   └── ingest/PLAN-B.md         the manual fallback for /ingest — lives WITH the skill it rescues
│   └── settings.json                wires it up, and its safety hooks, the moment you clone
├── system/                          the programs that do the sorting, plus the safety guards
├── shared/                          the piece that knows where your writing lives
├── docs/                            reference notes, and REPORT-A-BUG.md until the harness installer lands
├── .gitignore                       the line that keeps `data` out of git — do not edit
├── .gitattributes                   keeps line endings sane across Mac and Windows
├── CLAUDE.md                        the standing instructions every session opens with
├── memory/                          LEGACY, and empty. Your writing is NOT here — see its README.
│
└── data/                        <- YOURS. ignored by git. the only thing worth backing up.
    ├── canon.md                     the things about you that stay true
    ├── system/journal.md            what happened, as it happens
    ├── system/project-registry.md   so a cold session can find an old project
    ├── state/projects/              project notes
    └── desks/                       a folder per subject — built by your first ingest
        ├── <subject>/               one per pile the ingest finds in your own material
        └── <subject>/
```

**The split is still the whole design — but it is now enforced by `.gitignore`, not by folder
distance.** Everything sent to you is tracked by git. Everything *you* write lives in `data`, including
the desks your ingest builds, and git is told to ignore it completely: never tracked, never committed,
never uploaded.

⭐ **And you open the top folder — the one the tool itself is in.** That is what lets Claude find the
`/ingest` command at all. Opening a folder above it or below it is the single most common way this goes
wrong.

## Taking an update later

**Ask Claude:** *"check if there's an update to my brain and install it."*

⛔⛔ **THE ONE RULE THAT MATTERS: UPDATE WITH `git pull`. NEVER BY DELETING THIS FOLDER AND DOWNLOADING A
FRESH COPY.**

```bash
git pull
```

**A pull replaces the tool files and leaves `data` completely alone**, because git ignores it and
therefore never touches it. That is the safe path, and it is the only one anybody should use.

⚠ **Deleting the folder and re-cloning would take your writing with it.** Under the layout used before
2026-08-12 that was survivable — `data` sat outside the repository, so wiping the tool folder could not
reach it. **It sits inside now, so that safety net is gone.** If you ever genuinely need a fresh copy of
the tool, move `data` out first and move it back afterwards:

```bash
mv data ~/Desktop/data-keep      # then delete + re-clone, then:
mv ~/Desktop/data-keep data
```

⭐ **Before any update, the honest check is one command.** If it prints nothing at all, `data` is
properly ignored and a pull cannot touch it:

```bash
git status --porcelain
```

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
- **Your own identifiers — which calendar, which spreadsheet — live in your AI Brain folder**, at
  `config/`, never in this repository. Same rule as everything else you own.
- **It is a sit-down, not a click.** Expect to do it with someone the first time.

⛔ **Until you have done that sit-down, do not run an authentication flow on your own and do not hand
your account details to anything.** Nothing here needs them yet.

## What the sit-down covers

Do these in order, together, once. None of it is needed to use everything else in this package.

**1 — Install `gws` and log in.** It is the command-line tool that talks to Google. Install it however
your machine installs things, then run its login. **`gws` will ask which scopes to grant — Calendar,
Tasks, Sheets, Gmail, and others.** Grant only the ones you actually intend to use. Whatever you do not
grant, nothing in this package can reach at all — that is the strongest protection there is, and it
costs nothing to leave a scope off until you actually need it. **"What each scope reaches, and what
refuses it," right below, spells out exactly what saying yes to each one turns on** — read it before you
answer `gws`'s prompt, not after. Check the install landed and the login took:

```bash
command -v gws          # a path means it is installed
gws auth status         # says which account is connected
```

⛔ **Never `gws auth logout`, and never delete or move `~/.config/gws/`.** That directory is the
login for every window on this machine, and there is no undo — you would redo this sit-down. If
something looks broken, run `gws auth status` and read what it says before touching anything.

**2 — Put your own identifiers in your AI Brain folder, not in this repo.** Which calendar, which task
list, which spreadsheet — those are yours, and they are the kind of thing a public repository must
never carry. They live at `<notes>/config/`, one small file per thing, named so a stranger could tell
what it is:

```
<notes>/config/sheets.md     # "billing tracker → 1AbC...", one line per sheet you use
<notes>/config/cal.md        # up to four identifiers — see below
```

`cal.md` holds up to four `key: value` lines, and each one is what a guard below checks a write
against — an id that is not on file means the write it protects has nowhere safe to go, and is refused
rather than guessed at:

```
personal_calendar: you@example.com     # the calendar your life is already in — read only, never written to
agent_calendar:    abc123...@group.calendar.google.com   # the ONE calendar this system may write to
goals_tasklist:    <id>                # your goals list — protected, see the Tasks row below
daily_parent_task: <id>                # the one task your day's plan may hang subtasks from
```

A skill that needs an id reads it from there. If the file is not there, the skill says so rather than
guessing — which is the correct behaviour, and the reason nothing is pre-filled.

**3 — `clasp`, only if you want Apps Script.** `clasp` is Google's command-line tool for Apps Script,
and `/google-sheet` uses it for logic a formula cannot express. **Skip this unless you hit that wall** —
formulas, `ARRAYFORMULA` and the self-check layer all work with no clasp installed at all, and most
sheets never need it. If you do install it, its credential (`~/.clasprc.json`) is machine-local and
must never be committed, exactly like the `gws` login.

## What each scope reaches, and what refuses it

**Saying yes to a scope in `gws auth login` turns on everything in its row below — read AND write
both.** `gws` itself has no separate "read-only" grant; the right-hand column is what a guard in this
package refuses once you have said yes, not something Google withholds on its own. Say no to a scope
and none of this applies — nothing here can reach that service at all, guarded or not, which is why
"only the scopes you actually intend to use" in STEP 1 above is the real first line of defense.

| Scope | What connecting it lets the agent do | What is refused, always |
|---|---|---|
| **Calendar** | Read any calendar you can see (events, free/busy). Write ONLY to the one calendar named `agent_calendar` in `<notes>/config/cal.md`. | Every other write — to `primary`, to any other calendar, or anywhere at all if `agent_calendar` is not set. `guard_calendar_writes.sh` is default-deny: it recognises a fixed list of READ verbs and refuses every write, including one it has never seen spelled that way before. |
| **Tasks** | Read any task list. Write anywhere EXCEPT the list named `goals_tasklist`. Inside that one list, only subtasks under `daily_parent_task` — the day's plan — may be written. | Deleting or clearing anything on `goals_tasklist`, ever — no confirm path exists for that one, because Google Tasks keeps no version history and a deleted task is simply gone. `guard_tasks_writes.sh` decides with a real parser (`shlex` tokenizing, `json.loads` on the body), not a text match — the text-match version it replaced had seventeen working bypasses found across two rounds of adversarial testing on this exact guard. |
| **Sheets** | Read any spreadsheet. Write to one, but only after this session has read that sheet's own `_LLM_GUIDE` tab (once per sheet, good for twelve hours) — every sheet this system builds carries one. | A destructive op — clear, delete, mass-overwrite — or a structural one — adding/removing tabs, columns, formatting — without an in-the-moment human "yes" typed as `LIFEHACK_SHEET_CONFIRM=1` in front of the command; the agent is expected to ask first, never to add that itself. Separately, **any** write that would land on a cell holding a formula or a 🔒 mark is refused outright, confirm-flag or not, on any sheet the account can reach at all — appending a new row is always fine, since it never overwrites an existing cell. |
| **Gmail** | Read subjects, senders and dates freely. Read a message BODY only through the sanitizer (a raw body pull is blocked the same way a raw web page is). Move a label — file, archive, mark. **Nothing here composes or sends mail; that capability does not exist anywhere in this package.** | Deleting, batch-deleting, or trashing a message or thread — outright, unconditionally, no confirm path at all. `guard_gmail_destructive.sh` blocks the verb regardless of anything else true about the command. If mail genuinely needs to go, that happens in the Gmail UI, by you, where you can see what is about to disappear. |
| **`gws auth logout`** | *(not a scope — a command)* | Blocked outright, unconditionally, no confirm path. It clears every window's Google credentials at once with no undo; only you, at a terminal, ever run it — see the safety rule at the top of this section. |

⚠ **Read every row above as a strong speed bump, never as a lock — the guards say this about
themselves, in their own comments.** Each one reads a shell command as TEXT before deciding, and a
shell has effectively unlimited equivalent ways to spell the same command — a text check is always one
phrasing behind someone determined to get past it. This is not hypothetical: in the system these guards
were ported from, two independent adversarial passes attacked this same design — the first found 20
bypasses in about 20 minutes, a rewrite closed those and a second pass found 13 more, and after three
rounds of hardening only 1 of 27 tested attack forms still got through. The hardening that survived that
shipped here with the guards themselves, dated in each file's own header — a real parser (not a text
match) behind Tasks; on Calendar, Sheets and Gmail, matching the `gws` binary as a token anywhere in the
command, rather than requiring it sit directly beside the service word, which is what closed a
variable-substitution bypass found on 2026-08-14. The adversarial re-test of this exact copy has not
been repeated here.

**What these guards are good for:** stopping an ordinary mistake, an unreviewed script, or a model that
simply did not think to check. **What they are not:** a defense against someone deliberately trying,
from inside the same session, to talk their way around them.

---

# WHAT DOES NOT WORK YET — read this once, honestly

Two gaps, named so a reader who runs into one of them knows it is expected, not a broken install.
⚠ **CORRECTED 2026-08-15:** this section used to say nothing here runs on a schedule at all. That
was true when it was written and stopped being true once `system/tools/pulse.sh` (the heartbeat
daemon) and `system/tools/install-schedulers.sh` (which writes the cron/Task-Scheduler entry for
you — see that script) landed. **This package does have a scheduler now.** `install-schedulers.sh`
replays the job list in `system/pulse-config.md` onto your machine's own scheduler (cron on
Mac/Linux, Task Scheduler on Windows); until you run it, nothing fires on its own — that one-time
setup step is the real remaining gap, not an absent mechanism.

**A few ported tools still have nothing that calls them.** Most pieces under `system/tools/` and
`shared/tools/` that were built to run on a cadence now have a `pulse-config.md` row — including
the email-reading tools' writer (`email_summary_sync.py`, called by `email-summary-write-run.sh`
every 3 hours). A handful genuinely do not yet: check `system/pulse-config.md` for the live list of
what's wired rather than trusting a skill file's own claim about its schedule, which can drift out
of date exactly the way this section just did. If a skill's own file talks about something happening
"daily" or "on a cadence" and you're not sure it's real, that file is the one to check.

**`PUSH-FORWARD.md`, at the root of this folder, is the fuller and more current list, if your clone has
it.** ⚠ As of this writing it is untracked by git in the working copy this file was written from —
nobody has yet ruled on whether it ships as part of what `git clone` actually gives you. If it is
there, read it; it is the more current source. If it is not, the two points above are what we know of
either way.

---

# FILING A BUG — `gh` and a free GitHub account, only if you use it

Reporting a problem the fast way — saying **"file a bug"** and having the whole thing written up and
sent for you — needs the `gh` command-line tool and a free GitHub account. Neither is required for
anything else in this package; you can always just describe a problem in chat instead.

**Setting it up is its own five-minute walkthrough, separate from this one:** drag
`docs/REPORT-A-BUG.md` into the chat and say **"Set up bug reports."** It installs `gh` for you on a
Mac; on Windows it fetches it with `winget`, or sends you to the one page that works if `winget` isn't
there. You never type a command yourself.

**Cost:** both free. `gh` is GitHub's own tool, and the free tier of a GitHub account is all this
needs — no card.

---

# SCREENSHOTS FOR DESIGN WORK — Google Chrome, only if you use `/design-lifehack`

`/design-lifehack` looks at its own work by rendering a page to an image first
(`system/tools/render_shot.sh`), so Claude can actually see what it built instead of guessing from the
markup. That needs **Google Chrome** installed — a normal, free browser install, nothing special about
it. Nothing else in this package touches it; skip this if you never use that one skill.

**Getting it:** the ordinary download at <https://www.google.com/chrome/>, installed like any other
application. No account, no extension, nothing to configure afterwards.

⚠ **Verified on macOS only.** The tool also checks the standard Linux and Windows install locations,
but nobody has confirmed those work yet — if it can't find Chrome, it says so plainly rather than
failing silently.

Without it, that one skill's screenshots fail outright; every other skill in this package is
unaffected.

---

# `/ship` NEEDS TO KNOW WHO YOU ARE — one file, before its first run

If you ever use `/ship` to publish work to a public repository, its first run will refuse — on
purpose. It has no idea yet what must never be published: your name, your handles, anything that
would identify you. Nothing else in this package needs this file; skip this section entirely until
you actually use `/ship`.

**Make it once, before that first run:**

```bash
cd "$(git rev-parse --show-toplevel)" && python3 system/shipping-lane/identity_rules.py --write-example
```

**Say what that did, in one sentence:** it wrote a starter file at `<notes>/config/ship-identity.md`
— inside their own `data` folder, never inside this repository. Then open that file and swap the
example names in it for your own, one per line.

⚠ **This is not a workaround you can skip past — the lane fails closed instead.** Running `/ship`
with no identity file does not quietly proceed without your personal check; it refuses every single
time, and says exactly why. That is correct behaviour, not a bug: the alternative is a "clean" result
with your own name still sitting in a file. Full detail is in `.claude/skills/ship/SKILL.md`, under
**"FIRST RUN."**
